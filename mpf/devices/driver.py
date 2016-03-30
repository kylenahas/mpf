""" Contains the Driver parent class. """
import copy

from mpf.core.system_wide_device import SystemWideDevice


class Driver(SystemWideDevice):
    """Generic class that holds driver objects.

    A 'driver' is any device controlled from a driver board which is typically
    the high-voltage stuff like coils and flashers.

    This class exposes the methods you should use on these driver types of
    devices. Each platform module (i.e. P-ROC, FAST, etc.) subclasses this
    class to actually communicate with the physical hardware and perform the
    actions.

    Args: Same as the Device parent class

    """

    config_section = 'coils'
    collection = 'coils'
    class_label = 'coil'

    def __init__(self, machine, name):
        super().__init__(machine, name)

        self.time_last_changed = 0
        self.time_when_done = 0

    def prepare_config(self, config, is_mode_config):
        del is_mode_config
        config['number_str'] = str(config['number']).upper()
        return config

    def validate_and_parse_config(self, config, is_mode_config):
        platform = self.machine.get_platform_sections('coils', getattr(config, "platform", None))
        if platform.get_coil_config_section():
            self.machine.config_validator.validate_config(
                self.config_section, config, self.name, base_spec=platform.get_coil_config_section())
        else:
            super().validate_and_parse_config(config, is_mode_config)

        return config

    def _initialize(self):
        self.load_platform_section('coils')

        self.hw_driver, self.number = (
            self.platform.configure_driver(self.config))

    def validate_driver_settings(self, **kwargs):
        return self.hw_driver.validate_driver_settings(**kwargs)

    def enable(self, **kwargs):
        """Enables a driver by holding it 'on'.

        If this driver is configured with a holdpatter, then this method will use
        that holdpatter to pwm pulse the driver.

        If not, then this method will just enable the driver. As a safety
        precaution, if you want to enable() this driver without pwm, then you
        have to add the following option to this driver in your machine
        configuration files:

        allow_enable: True

        """
        del kwargs

        self.time_when_done = -1
        self.time_last_changed = self.machine.clock.get_time()
        self.log.debug("Enabling Driver")
        self.hw_driver.enable(self)

    def disable(self, **kwargs):
        """ Disables this driver """
        del kwargs
        self.log.debug("Disabling Driver")
        self.time_last_changed = self.machine.clock.get_time()
        self.time_when_done = self.time_last_changed
        self.machine.delay.remove(name='{}_timed_enable'.format(self.name))
        self.hw_driver.disable(self)

    def pulse(self, milliseconds=None, power=None, **kwargs):
        """ Pulses this driver.

        Args:
            milliseconds: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            power: A multiplier that will be applied to the default pulse time,
                typically a float between 0.0 and 1.0. (Note this is can only be used
                if milliseconds is also specified.)
        """
        del kwargs

        # todo power is broken with fast since they come in as strings

        if not milliseconds:
            if self.config['pulse_ms']:
                milliseconds = self.config['pulse_ms']
            else:
                milliseconds = self.machine.config['mpf']['default_pulse_ms']

        if power and isinstance(milliseconds, int):
            milliseconds *= power
        else:
            power = 1.0

        if isinstance(milliseconds, str) or (
                isinstance(milliseconds, int) and 0 < milliseconds <= self.platform.features['max_pulse']):
            self.log.debug("Pulsing Driver. %sms (%s power)", milliseconds,
                           power)
            ms_actual = self.hw_driver.pulse(self, milliseconds)
        else:
            self.log.debug("Enabling Driver for %sms (%s power)", milliseconds,
                           power)
            self.machine.delay.reset(name='{}_timed_enable'.format(self.name),
                                     ms=milliseconds,
                                     callback=self.disable)
            self.enable()
            self.time_when_done = self.time_last_changed + (
                milliseconds / 1000.0)
            ms_actual = milliseconds

        if ms_actual != -1:
            self.time_when_done = self.time_last_changed + (ms_actual / 1000.0)
        else:
            self.time_when_done = -1

    def timed_enable(self, milliseconds, **kwargs):
        del kwargs
        self.pulse(milliseconds)

    def _check_platform(self, switch):
        # TODO: handle stuff in software if platforms differ
        if self.platform != switch.platform:
            raise AssertionError("Switch and Coil have to use the same platform")

    def set_pulse_on_hit_and_release_rule(self, enable_switch):
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_and_release_rule(enable_switch, self)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch):
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_and_enable_and_release_rule(enable_switch, self)

    def set_pulse_on_hit_rule(self, enable_switch):
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_rule(enable_switch, self)

    def clear_hw_rule(self, switch):
        self.platform.clear_hw_rule(switch, self)


class ReconfiguredDriver(Driver):
    def __init__(self, driver, config_overwrite):
        # no call to super init
        self._driver = driver
        self._config_overwrite = config_overwrite

    def __getattr__(self, item):
        return getattr(self._driver, item)

    @property
    def config(self):
        config = copy.deepcopy(self._driver.config)
        for name, item in self._config_overwrite.items():
            if item is not None:
                config[name] = item

        return config
