// SPDX-License-Identifier: GPL-2.0-only
/*
 * LED Kernel Trigger for SIM Card & Modem State on MSM8916
 * Author: Jony (MSM8916 Embedded R&D)
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/leds.h>
#include <linux/slab.h>
#include <linux/device.h>

enum sim_state {
	SIM_STATE_MISSING = 0,
	SIM_STATE_SEARCHING,
	SIM_STATE_READY,
};

struct sim_trig_data {
	struct led_classdev *led_cdev;
	enum sim_state state;
};

static struct led_trigger *sim_led_trigger;

static ssize_t sim_state_show(struct device *dev,
			      struct device_attribute *attr, char *buf)
{
	struct led_classdev *led_cdev = dev_get_drvdata(dev);
	struct sim_trig_data *data = led_trigger_get_drvdata(led_cdev);

	switch (data->state) {
	case SIM_STATE_MISSING:
		return sprintf(buf, "missing\n");
	case SIM_STATE_SEARCHING:
		return sprintf(buf, "searching\n");
	case SIM_STATE_READY:
		return sprintf(buf, "ready\n");
	default:
		return sprintf(buf, "unknown\n");
	}
}

static ssize_t sim_state_store(struct device *dev,
			       struct device_attribute *attr,
			       const char *buf, size_t size)
{
	struct led_classdev *led_cdev = dev_get_drvdata(dev);
	struct sim_trig_data *data = led_trigger_get_drvdata(led_cdev);
	unsigned long delay_on = 0, delay_off = 0;

	if (sysfs_streq(buf, "missing") || sysfs_streq(buf, "none")) {
		data->state = SIM_STATE_MISSING;
		/* Fast blink: 150ms on / 150ms off */
		delay_on = 150;
		delay_off = 150;
		led_blink_set(led_cdev, &delay_on, &delay_off);
	} else if (sysfs_streq(buf, "searching") || sysfs_streq(buf, "registering")) {
		data->state = SIM_STATE_SEARCHING;
		/* Slow blink: 1000ms on / 1000ms off */
		delay_on = 1000;
		delay_off = 1000;
		led_blink_set(led_cdev, &delay_on, &delay_off);
	} else if (sysfs_streq(buf, "ready") || sysfs_streq(buf, "registered")) {
		data->state = SIM_STATE_READY;
		/* Solid on */
		led_blink_set(led_cdev, &delay_on, &delay_off);
		led_set_brightness_nosleep(led_cdev, led_cdev->max_brightness);
	} else {
		return -EINVAL;
	}

	return size;
}

static DEVICE_ATTR_RW(sim_state);

static struct attribute *sim_trig_attrs[] = {
	&dev_attr_sim_state.attr,
	NULL
};
ATTRIBUTE_GROUPS(sim_trig);

static int sim_trig_activate(struct led_classdev *led_cdev)
{
	struct sim_trig_data *data;

	data = kzalloc(sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;

	data->led_cdev = led_cdev;
	data->state = SIM_STATE_MISSING;
	led_set_trigger_data(led_cdev, data);

	/* Default state: missing (fast blink) */
	led_set_brightness_nosleep(led_cdev, LED_OFF);
	return 0;
}

static void sim_trig_deactivate(struct led_classdev *led_cdev)
{
	struct sim_trig_data *data = led_trigger_get_drvdata(led_cdev);

	if (data) {
		led_set_brightness_nosleep(led_cdev, LED_OFF);
		kfree(data);
	}
}

static struct led_trigger sim_trigger_def = {
	.name = "simcard",
	.activate = sim_trig_activate,
	.deactivate = sim_trig_deactivate,
	.groups = sim_trig_groups,
};

static int __init sim_trig_init(void)
{
	return led_trigger_register(&sim_trigger_def);
}

static void __exit sim_trig_exit(void)
{
	led_trigger_unregister(&sim_trigger_def);
}

module_init(sim_trig_init);
module_exit(sim_trig_exit);

MODULE_AUTHOR("Jony <msm8916-dev>");
MODULE_DESCRIPTION("SIM Card Status LED Trigger");
MODULE_LICENSE("GPL v2");
