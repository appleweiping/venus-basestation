#ifndef motion_functions
#define motion_functions

#include <libpynq.h>
#include <stepper.h>

typedef enum {
    LEFT,
    RIGHT,
} side; 

void motionInit(int speed_0_to_100, int* distance_register);

void move(int distance_in_cm);

void turn90(side turning_side);

void orient();

bool moving(void);

void motionDestroy(void);
// display_init + displayString + initialise static font
#endif