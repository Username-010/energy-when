"""Energy When — cheapest time to run a load, with solar."""

DOMAIN = "energy_when"

CONF_PRICE_SENSOR = "price_sensor"
CONF_SURCHARGE = "surcharge"
CONF_ALL_IN_SENSOR = "all_in_sensor"
CONF_SOLAR_NOW = "solar_now"
CONF_SOLAR_REMAINING = "solar_remaining"
CONF_SOLAR_TOMORROW = "solar_tomorrow"
CONF_HOUSE_POWER = "house_power"
CONF_DURATION = "duration_h"
CONF_APPLIANCE_W = "appliance_w"
CONF_BASE_LOAD_W = "base_load_w"

DEFAULT_SURCHARGE = 0.11
DEFAULT_DURATION = 2.5
DEFAULT_APPLIANCE_W = 600
DEFAULT_BASE_LOAD_W = 800
