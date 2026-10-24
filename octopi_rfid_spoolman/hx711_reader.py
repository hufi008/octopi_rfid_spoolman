"""Low-level HX711 reader for the OctoPrint RFID Spoolman plugin.

The reader deliberately does not assume a calibration factor. Calibrate the
assembled load cell before using read_weight() or sending measurements to
Spoolman.

Pins use Raspberry Pi BOARD (physical pin) numbering by default. This is
intentional: the RC522 library used by this plugin configures RPi.GPIO in
BOARD mode, and RPi.GPIO's numbering mode is global to the process.
"""

import statistics
import time

import RPi.GPIO as GPIO


class HX711Reader:
    """Read a 24-bit HX711 ADC connected to a load cell."""

    def __init__(
        self,
        dout_pin=38,
        sck_pin=40,
        gain=128,
        reference_unit=None,
        offset=0.0,
        ready_timeout=2.0,
    ):
        if gain not in (128, 64, 32):
            raise ValueError("gain must be 128, 64, or 32")
        if reference_unit is not None and reference_unit == 0:
            raise ValueError("reference_unit must not be zero")

        self.dout_pin = int(dout_pin)
        self.sck_pin = int(sck_pin)
        self.gain = gain
        self.reference_unit = reference_unit
        self.offset = float(offset)
        self.ready_timeout = float(ready_timeout)
        self._closed = False

        mode = GPIO.getmode()
        if mode is None:
            GPIO.setmode(GPIO.BOARD)
        elif mode != GPIO.BOARD:
            raise RuntimeError(
                "RPi.GPIO is already using BCM numbering; HX711Reader expects "
                "BOARD numbering so it can coexist with the RC522 reader."
            )

        GPIO.setup(self.dout_pin, GPIO.IN)
        GPIO.setup(self.sck_pin, GPIO.OUT, initial=GPIO.LOW)
        time.sleep(0.1)

    def _wait_ready(self, timeout=None):
        timeout = self.ready_timeout if timeout is None else float(timeout)
        deadline = time.monotonic() + timeout
        while GPIO.input(self.dout_pin) != GPIO.LOW:
            if time.monotonic() >= deadline:
                raise TimeoutError("HX711 did not become ready before timeout")
            time.sleep(0.001)

    def read_raw(self, timeout=None):
        """Read one signed 24-bit sample from the HX711."""
        if self._closed:
            raise RuntimeError("HX711Reader is closed")

        self._wait_ready(timeout)
        value = 0
        for _ in range(24):
            GPIO.output(self.sck_pin, GPIO.HIGH)
            value = (value << 1) | int(GPIO.input(self.dout_pin))
            GPIO.output(self.sck_pin, GPIO.LOW)

        # The next pulse selects the gain/channel for the next conversion.
        pulses = {128: 1, 32: 2, 64: 3}[self.gain]
        for _ in range(pulses):
            GPIO.output(self.sck_pin, GPIO.HIGH)
            GPIO.output(self.sck_pin, GPIO.LOW)

        # Convert two's-complement 24-bit output to a signed Python integer.
        if value & 0x800000:
            value -= 1 << 24
        return value

    def read_average(self, samples=5, timeout=None):
        """Return the median of several raw readings to reduce spike noise."""
        if isinstance(samples, bool) or int(samples) < 1:
            raise ValueError("samples must be a positive integer")
        readings = [self.read_raw(timeout=timeout) for _ in range(int(samples))]
        return float(statistics.median(readings))

    def tare(self, samples=10):
        """Set the raw zero offset with the load cell unloaded."""
        self.offset = self.read_average(samples=samples)
        return self.offset

    def read_weight(self, samples=5, timeout=None):
        """Return calibrated weight units (normally grams).

        reference_unit is the raw-counts-per-unit calibration factor. It must
        be established with a known mass; no default calibration is assumed.
        """
        if self.reference_unit is None:
            raise RuntimeError(
                "HX711 is not calibrated: set reference_unit using a known mass"
            )
        if self.reference_unit == 0:
            raise ValueError("reference_unit must not be zero")
        raw = self.read_average(samples=samples, timeout=timeout)
        return (raw - self.offset) / float(self.reference_unit)

    def close(self):
        """Release only this reader's GPIO pins, leaving the RC522 untouched."""
        if self._closed:
            return
        try:
            GPIO.output(self.sck_pin, GPIO.LOW)
        finally:
            GPIO.cleanup([self.dout_pin, self.sck_pin])
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
