#ifndef motion_functions
#define motion_functions

#include <libpynq.h>
#include <stepper.h>

typedef enum {
    LEFT,
    RIGHT,
} side; 

void motionInit(int speed_0_to_100);

void move(int distance_in_cm);

void turn90(int turning_side);

void orient(void);

bool moving(void);

void motionDestroy(void);
// display_init + displayString + initialise static font
#endif