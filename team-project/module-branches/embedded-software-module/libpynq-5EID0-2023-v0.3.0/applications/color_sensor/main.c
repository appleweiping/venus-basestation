#include <libpynq.h>
#include "tcs3200.h"

int main(void)
{
    pynq_init();
    init_color_sensor();

    while (1)
    {
        get_color();
        sleep_msec(500);
    }

    destroy_color_sensor();
    pynq_destroy();
    return 0;
}
