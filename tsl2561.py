from machine import I2C
from math import pow

T_FAST   = const(0b00)
T_MEDIUM = const(0b01)
T_SLOW   = const(0b10)
T_MANUAL = const(0b11)

class TSL2561(object):
    """
    This class implements an interface to the TSL2561 luminosity sensor from 
    TAOS Inc. now blonging to the ams AG.
    
    ToDos:
    * Interrupt control including thresholds
    """

    def __init__(self, i2c, addr=0x39):
        """
        Initialize a sensor object on the given I2C bus and accessed by the
        given address. If no address is given the default address 0x39 for 
        this sensor family is used.
        Sets the sensor to power down mode after initialization.
        """
        if i2c == None or i2c.__class__ != I2C:
            raise ValueError('I2C object needed as argument!')
        self._i2c = i2c
        self._addr = addr
        if not self._i2c.is_ready(self._addr):
            raise Exception("SHT31 not found on address %s" % hex(self._addr))
        self.set_power_up(True)
        self.set_power_up(False)

    def _send(self, buf):
        """
        Sends the given buffer object over I2C to the sensor.
        """
        self._i2c.send(buf, self._addr)

    def _recv(self, n):
        """
        Read bytes from the sensor using I2C. The byte count can be specified
        as an argument.
        Returns a bytearray for the result.
        """
        return self._i2c.recv(n, self._addr)

    def set_power_up(self, s=True):
        """
        Sends an power command to the sensor. A boolean argument can be 
        passed to this method. By setting the argument to False the seonsor 
        can be powered down to conserve power.
        An additional feature while powering the soensor up is that it must 
        actively acknowledge the power up command. This can be used to check 
        the communication with the sensor.
        """
        if s.__class__ != bool:
            raise ValueError('Boolean object needed as argument!')
        b = bytearray()
        b.append(0b10000000)
        if s:
            b.append(0b11)
        else:
            b.append(0)
        self._send(b)
        if s:
            if self._recv(1) == 0b11:
                raise("Startup of TSL2561 sensor failed!" )
    
    def set_timing_gain(self, timing=T_SLOW, gain=False, manual_start=True):
        """
        Controls the sensor integration time period and gain. It is also 
        possible to select manual timing mode. When using this mode the 
        manual start argument must be set to either True or False to start or 
        stop the integration timer. 
        Gain can be switched either on or off and can be used to activate a 
        16x gain to the sensor reading.
        Integration times for the different modes are:
          T_HIGH - 
        """
        if timing not in (T_FAST, T_MEDIUM, T_SLOW, T_MANUAL):
            raise ValueError('Wrong value for timing argument!')
        if gain.__class__ != bool:
            raise ValueError('Boolean object needed as gain argument!')
        if manual_start.__class__ != bool:
            raise ValueError('Boolean object needed as manual start/stop argument!')
        b = bytearray()
        b.append(0b10000001)
        b.append(gain << 4 | manual_start << 3 | timing)
        self._gain = gain
        self._timing = timing
        self._send(b)
    
    def get_id(self):
        """
        Reads the ID register of the sensor and returns a tuple containing 
        the part and revision number.
        """
        b = bytearray()
        b.append(0b10001010)
        self._send(b)
        id_reg = self._recv(1)[0]
        p_no = id_reg >> 4
        r_no = id_reg & 0b1111
        return (p_no, r_no)
    
    def _raw_lumi(self):
        """
        Read the raw luminosity from the sensor.
        """
        self._send(0b10001100)
        c0_l = self._recv(1)[0]
        self._send(0b10001101)
        c0_h = self._recv(1)[0]
        self._send(0b10001110)
        c1_l = self._recv(1)[0]
        self._send(0b10001111)
        c1_h = self._recv(1)[0]
        c0 = c0_h * 256 + c0_l
        c1 = c1_h * 256 + c1_l
        if not self._gain:
            c0 = c0 << 4
            c1 = c1 << 4
        return c0, c1

    def get_lumi(self):
        """
        Read the luminosity in units of Lux.
        """
        raw = self._raw_lumi()
        l = 0
        if raw[0] != 0:
            c = raw[1] / raw[0]
            if c > 0:
                if c <= 0.5:
                    l = 0.0304 * raw[0] - 0.062 * raw[0] * pow(c, 1.4)
                elif c <= 0.61:
                    l = 0.0224 * raw[0] - 0.031 * raw[1]
                elif c <= 0.8:
                    l = 0.0128 * raw[0] - 0.0153 * raw[1]
                elif c <= 1.3:
                    l = 0.00146 * raw[0] - 0.00112 * raw[1]
                else:
                    l = 0
        return l
