#include "tcs3200.h"
#include <libpynq.h>
#include <stdio.h>

#define S0  IO_A0
#define S1  IO_A1
#define S2  IO_A2
#define S3  IO_A3
#define OUT IO_A4

#define SETTLE_MS   50
#define LOOP_COUNT  50000

static int read_channel(int s2, int s3)
{
    gpio_set_level(S2, s2);
    gpio_set_level(S3, s3);
    sleep_msec(SETTLE_MS);

    int count = 0;
    int last = gpio_get_level(OUT);

    for (int i = 0; i < LOOP_COUNT; i++)
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

static int classify(int r, int g, int b)
{
    if (r > 3000 && g > 2000 && b > 3000)  return COLOR_WHITE;
    if (g >= 1200)                           return COLOR_GREEN;
    if (g >= 1080 && g <= 1180)             return COLOR_BLUE;
    if (g >= 860  && g <= 910)              return COLOR_RED;
    if (r < 1500  && g < 1000 && b < 1500) return COLOR_BLACK;
    return COLOR_UNKNOWN;
}

static const char *color_name(int c)
{
    switch (c) {
        case COLOR_WHITE:   return "WHITE";
        case COLOR_GREEN:   return "GREEN";
        case COLOR_BLUE:    return "BLUE";
        case COLOR_RED:     return "RED";
        case COLOR_BLACK:   return "BLACK";
        default:            return "UNKNOWN";
    }
}

int init_color_sensor(void)
{
    gpio_init();

    gpio_set_direction(S0, GPIO_DIR_OUTPUT);
    gpio_set_direction(S1, GPIO_DIR_OUTPUT);
    gpio_set_direction(S2, GPIO_DIR_OUTPUT);
    gpio_set_direction(S3, GPIO_DIR_OUTPUT);
    gpio_set_direction(OUT, GPIO_DIR_INPUT);

    gpio_set_level(S0, 1);
    gpio_set_level(S1, 1);

    return 1;
}

int get_color(void)
{
    int r = read_channel(0, 0);
    int b = read_channel(0, 1);
    int g = read_channel(1, 1);

    int color = classify(r, g, b);

    printf("R:%d G:%d B:%d -> %s\n", r, g, b, color_name(color));
    fflush(stdout);

    return color;
}

void destroy_color_sensor(void)
{
}
