#include <stdio.h>
#include <libpynq.h>

#define S0  IO_A0
#define S1  IO_A1
#define S2  IO_A2
#define S3  IO_A3
#define OUT IO_A4

int read_color(int s2, int s3)
{
    gpio_set_level(S2, s2);
    gpio_set_level(S3, s3);

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
    if (r < 800 && g < 1800 && b < 800)
        return "BLACK";

    if (r > 2500 && g > 6000 && b > 2500)
        return "WHITE";

    if (g > 3000)
        return "GREEN";

    if (r > 1350 && b > 1350)
        return "RED";

    if (r >= 900 && r <= 1250 && b >= 900 && b <= 1250)
        return "BLUE";

    return "UNKNOWN";
}

int main(void)
{
    pynq_init();
    gpio_init();

    gpio_set_direction(S0, GPIO_DIR_OUTPUT);
    gpio_set_direction(S1, GPIO_DIR_OUTPUT);
    gpio_set_direction(S2, GPIO_DIR_OUTPUT);
    gpio_set_direction(S3, GPIO_DIR_OUTPUT);
    gpio_set_direction(OUT, GPIO_DIR_INPUT);

    gpio_set_level(S0, 1);
    gpio_set_level(S1, 1);

    while (1)
    {
        int red = read_color(0, 0);
        int blue = read_color(0, 1);
        int green = read_color(1, 1);

        const char* color = decide_color(red, green, blue);

        printf("R:%d G:%d B:%d -> %s\n", red, green, blue, color);

        sleep_msec(500);
    }

    pynq_destroy();
    return 0;
}