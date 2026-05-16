#ifndef motion_functions
#define motion_functions

#include <libpynq.h>
#include <stepper.h>

#define CHAR_PER_LINE 20

void motionInit(int speed_0_to_100);

void move(int distance_in_cm);

bool moving(void);

void motionDestroy(void);
// display_init + displayString + initialise static font
#endif