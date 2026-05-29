#include "motion-functions.h"
#include <libpynq.h>
#include <stepper.h>
#include <mapping.h>
#define ratio 10

void motionInit(int speed_0_to_100) {
    stepper_init();
    stepper_enable();
    stepper_set_speed(10000, 10000);
}

/*TODO*/
void orient() {
    /* THIS FUNCTION SHOULD TURN THE ROBOT AT AN ANGLE SUCH THAT IT'S
    FORWARD TRAJECTORY IS PARALLEL TO THE BORDER */
    while (getColor() == "BLACK") {


    }
}

void move(int distance_in_cm) {
    float left,right;

    left = distance_in_cm * ratio;
    right = left;
    map_update(left, right);

    stepper_steps((int16_t)left, (int16_t)right);
    while(!stepper_steps_done()) continue;

    sleep_msec(100);
}
/*DOESN'T WORK!*/
// void move_check_update(int distance_in_cm) {
//   move(distance_in_cm);
//   while (!stepper_steps_done()) {

//     if (obstacle() || border) {
//       int16_t left_rest;
//       int16_t right_rest;

//       stepper_get_steps(&left_rest, &right_rest);

//       stepper_reset();
//       stepper_enable();

//       left = left - left_rest;
//       right = right - right_rest;

//       map_update(left, right);

//       return;
//     }

//     sleep_msec(10);
//   }

//   map_update(left, right);
// }

void turn90(int turning_side) {
    switch (turning_side) {
        case 0: //left
                stepper_steps(-1600, 1600);
            break;
        case 1: //right
                stepper_steps(1600, -1600);
            break;
        default:
            printf("Default case: turn90");
            break;

    }
}

bool moving() { return stepper_steps_done(); }

void motionDestroy() {
    stepper_destroy();

}
