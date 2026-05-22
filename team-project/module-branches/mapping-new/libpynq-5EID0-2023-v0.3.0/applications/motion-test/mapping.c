#include "mapping.h"
#include <libpynq.h>
#include <math.h>

/* TODO
    UPDATE THE CODE HERE WITH CODE FROM PAVEL
*/
#define PI 3.14159265359

// static int* distance_register; //Ideal distance register
// static int* turns_register; //+1 for every turn to the right

#define WHEEL_DIAMETER_CM  8
#define WHEEL_BASE_CM     12
#define STEPS_PER_ROT     1600// ADD

static float x = 0.0f;
static float y = 0.0f;
static float angle = 0.0f;
static float cm_per_step = 0.0157079632679489662f;

void map_init(void) {
    x = 0.0f;
    y = 0.0f;
    angle = 0.0f;

    cm_per_step = (PI * WHEEL_DIAMETER_CM) / (STEPS_PER_ROT);
}

void map_reset(void) {
    x = 0.0f;
    y = 0.0f;
    angle = 0.0f;
}

float getX() {return x;}
float getY() {return y;}

void map_update(int left_steps, int right_steps) {
    float sL = left_steps * cm_per_step;
    float sR = right_steps * cm_per_step;

    float dist = (sL + sR) / 2.0f;
    float da = (sR - sL) / WHEEL_BASE_CM;

    x += dist * cosf(angle + da / 2.0f);
    y += dist * sinf(angle + da / 2.0f);

    angle += da;

    if (angle > PI) {
        angle -= 2.0f * PI;
    } else if (angle < -PI) {
        angle += 2.0f * PI;
    }

    printf("X is %f\n Y is %f\n angle: %f\n", x, y, angle);
}