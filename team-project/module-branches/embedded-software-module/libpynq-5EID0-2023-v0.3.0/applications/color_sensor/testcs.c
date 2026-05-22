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
        int color = get_color();

        switch (color) {
            case COLOR_WHITE:   printf("WHITE\n");   break;
            case COLOR_BLUE:    printf("BLUE\n");    break;
            case COLOR_GREEN:   printf("GREEN\n");   break;
            case COLOR_BLACK:   printf("BLACK\n");   break;
            case COLOR_RED:     printf("RED\n");     break;
            default:            printf("UNKNOWN\n"); break;
        }

        sleep_msec(500);
    }

    destroy_color_sensor();
    pynq_destroy();
    return EXIT_SUCCESS;
}