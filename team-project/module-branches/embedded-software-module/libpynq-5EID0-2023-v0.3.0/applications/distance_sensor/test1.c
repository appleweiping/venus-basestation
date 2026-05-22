#include <libpynq.h>
#include <stdio.h>
#include <stdlib.h>

#include "v15310x.h"

int main(void) {
    pynq_init();
    setbuf(stdout, NULL);

    printf("program started\n");

    if (!init_distance_sensor()) {
        printf("distance sensor failed\n");
        destroy_distance_sensor();
        pynq_destroy();
        return EXIT_FAILURE;
    }

    printf("distance sensor initialized\n");

    while (1) {
        int distance = get_distance();

        if (distance >= 0) {
            printf("distance: %d mm\n", distance);
        } else {
            printf("distance: out of range / read failed\n");
        }

        sleep_msec(100);
    }

    destroy_distance_sensor();
    pynq_destroy();

    return EXIT_SUCCESS;
}