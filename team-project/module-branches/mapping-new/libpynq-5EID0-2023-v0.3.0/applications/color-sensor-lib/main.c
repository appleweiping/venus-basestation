#include <libpynq.h>
#include "tcs3200.h"   // gives you get_color() and the COLOR_* constants

int main(void) {
    pynq_init();

    if (!init_color_sensor()) {
        printf("Color sensor init failed\n");
        pynq_destroy();
        return EXIT_FAILURE;
    }

    while (1) {
        const char* color = get_color();

        printf("Color is: %s\n", color);

        sleep_msec(500);
    }

    destroy_color_sensor();
    pynq_destroy();
    return EXIT_SUCCESS;
}