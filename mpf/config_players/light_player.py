from mpf.core.config_player import ConfigPlayer
from mpf.core.utility_functions import Util


class LightPlayer(ConfigPlayer):
    config_file_section = 'light_player'
    show_section = 'lights'
    machine_collection_name = 'lights'

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None, priority=0,
             play_kwargs=None, **kwargs):

        del kwargs

        if 'lights' in settings:
            settings = settings['lights']

        for light, s in settings.items():

            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            try:
                light.on(**s)
                if caller:
                    self.caller_target_map[caller].add(light)

            except AttributeError:
                try:
                    self._light_on(light, caller, **s)
                except KeyError:
                    light_list = Util.string_to_list(light)
                    if len(light_list) > 1:
                        for light1 in light_list:
                            self._light_on(light1, caller, **s)
                    else:
                        for light1 in self.machine.lights.sitems_tagged(light):
                            self._light_on(light1, caller, **s)

    def _light_on(self, light_name, caller=None, **s):
        self.machine.lights[light_name].on(**s)
        if caller:
            self.caller_target_map[caller].add(
                self.machine.lights[light_name])

    def clear(self, caller, priority):
        try:
            for light in self.caller_target_map[caller]:
                light.off(priority=0, force=True)
        except KeyError:
            pass

    def get_express_config(self, value):
        value = str(value).replace(' ', '').lower()
        fade = 0
        if '-f' in value:
            composite_value = value.split('-f')
            value = composite_value[0]
            fade = Util.string_to_ms(composite_value[1])

        return dict(brightness=value, fade_ms=fade)

player_cls = LightPlayer