#include "tcs3200.h"
#include <stdio.h>
#include <libpynq.h>

#define S0  IO_A0
#define S1  IO_A1
#define S2  IO_A2
#define S3  IO_A3
#define OUT IO_A4

/*STATUS: NOT WORKING - FIX CALLIBRATION*/


int read_color(int s2, int s3)
{
    gpio_set_level(S2, s2);
    gpio_set_level(S3, s3);

    // Give the sensor a moment to change filters and settle
    sleep_msec(50);

    int count = 0;
    int last = gpio_get_level(OUT);

    for (int i = 0; i < 50000; i++)
    {
        int now = gpio_get_level(OUT);

        if (now != last)
        {
            count++;
            last = now;
        }
    }

    return count;
}

const char* decide_color(int r, int g, int b)
{
    // BLACK / DARK (Not enough light reflecting back)
    if (r < 200 && g < 200 && b < 200) {
        return "BLACK";
    }

    // WHITE (All colors reflecting back strongly)
    // Note: You will likely need to tweak this threshold number
    // depending on your ambient lighting and how many loop iterations you run
    if (r > 1500 && g > 1500 && b > 1500) {
        return "WHITE";
    }

    // Find the dominant color by comparing them directly
    if (r > g && r > b && g > 200 && g > 200) {
        return "RED";
    }
    else if (g > r && g > b) {
        return "GREEN";
    }
    else if (b > r && b > g) {
        return "BLUE";
    }

    return "UNKNOWN";
}

int init_color_sensor() {
    gpio_init();

    gpio_set_direction(S0, GPIO_DIR_OUTPUT);
    gpio_set_direction(S1, GPIO_DIR_OUTPUT);
    gpio_set_direction(S2, GPIO_DIR_OUTPUT);
    gpio_set_direction(S3, GPIO_DIR_OUTPUT);
    gpio_set_direction(OUT, GPIO_DIR_INPUT);

    // CHANGE: Set frequency scaling to 2% (S0 = Low, S1 = High)
    // This lowers the maximum frequency to ~12 kHz so the software loop can catch the toggles
    gpio_set_level(S0, 0);
    gpio_set_level(S1, 1);

    return 1;
}

const char* get_color() {
    int red = read_color(0, 0);
    int blue = read_color(0, 1);
    int green = read_color(1, 1);

    const char* color = decide_color(red, green, blue);

    return color;
}
