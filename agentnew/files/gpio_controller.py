import logging

logger = logging.getLogger("EVC04_Agent.gpio_controller")


def export_gpio_pin(pin):
    try:
        f = open("/sys/class/gpio/export", "w")
        f.write(str(pin))
        f.close()
    except IOError:
        logger.info(
            "GPIO %s already Exists, so skipping export gpio" % str(pin))


def read_gpio_pin(pinNo):
    gpioPin = "gpio%s" % (str(pinNo), )
    pin = open("/sys/class/gpio/"+gpioPin+"/value", "r")
    value = pin.read()
    pin.close()
    return int(value)
