#include <libpynq.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stepper.h>
#include "../distance_sensor/vl53l0x.h"

#define THRESHOLD_MM 155
#define NORMAL_SPEED 40000
#define SLOW_SPEED 40000
#define STEPS_FORWARD 330
#define POLLING_DELAY_MS 1000

int main(void) {
    pynq_init();
    stepper_init();
    stepper_enable();

    if (!init_distance_sensor()) {
        printf("error distance sensor\n");
        stepper_destroy();
        pynq_destroy();
        return EXIT_FAILURE;
    }
    printf("ready\n");

    int saved_distance = -1;

    printf("Moving forward\n");
    stepper_set_speed(NORMAL_SPEED, NORMAL_SPEED);

    while (true) {
        int current_distance = get_distance();


        printf("%d\n", current_distance);


        if (current_distance > 0) {

            if (current_distance < THRESHOLD_MM) {
                saved_distance = current_distance;
                printf("Object at distance: %d\n", saved_distance);
                break;
            }
        }

        stepper_steps(100, 100);
        sleep_msec(POLLING_DELAY_MS);
    }

    sleep_msec(1000);

    stepper_set_speed(SLOW_SPEED, SLOW_SPEED);
    stepper_steps(STEPS_FORWARD, STEPS_FORWARD);

    sleep_msec(3000);

    int final_distance = get_distance();
    printf("step forward: new distance: %d\n", final_distance);

    if (final_distance > 125) {
        printf("object is : small block\n");
    }
    else if (final_distance >= 110 && final_distance <= 120) {
        printf("object is : big rock\n");
    }
    else if (final_distance < 110) {
        printf("object is : mountain\n");
    }
    else {
        printf("object is : unknown\n");
    }

    destroy_distance_sensor();
    stepper_destroy();
    pynq_destroy();

    return EXIT_SUCCESS;
}
