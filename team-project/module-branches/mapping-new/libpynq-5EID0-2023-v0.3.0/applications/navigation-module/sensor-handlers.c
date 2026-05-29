#include "sensor-handlers.h"
#include <libpynq.h>
#include "VL53L0X.h"

#define LIMIT_MM 70
#define SAMPLING_INTERVAL_GET_DISTANCE_MS 5
#define NUMBER_OF_SAMPLES_GET_DISTANCE 10

bool obstacle(void) {
    int index = 0;
    int sum = 0;

    for (int i = 0; i < (NUMBER_OF_SAMPLES_GET_DISTANCE-1); i++) {
        int distance = getDistance();
        if (distance == -1) {
            printf("[ERROR] Sampling too fast check sesnor-handlers:obstacle()\n");
            continue;
        }
        sum += getDistance();//connect the sensor
        sleep_msec(SAMPLING_INTERVAL_GET_DISTANCE_MS);
    }

    int avg = sum / NUMBER_OF_SAMPLES_GET_DISTANCE;
    if (avg < LIMIT_MM) {
        return true;
    }

    return false;
}


bool border() {
    return false;
}

bool raw_obstacle() {


}

char get_obstacle_color() {
    char *color[5];
    int pass = 0;

    while (pass == 0) {
        int index = 0;
        pass = 1;

        while (index < 5) {
            char *color_temp = getColor();

            color[index] = malloc(strlen(color_temp) + 1);
            strcpy(color[index], color_temp);

            sleep_msec(2);
            index++;
        }

        for (int i = 0; i < 4; i++) {
            if (strcmp(color[i], color[i + 1]) != 0) {
                pass = 0;
                break;
            }
        }

        if (pass == 0) {
            for (int i = 0; i < 5; i++) {
                free(color[i]);
            }
        }
    }

    char result = color[0][0];

    for (int i = 0; i < 5; i++) {
        free(color[i]);
    }

    return result;
}
