#include "mapping.h"
#include <libpynq.h>

static int* distance_register; //Ideal distance register
static int* turns_register; //+1 for every turn to the right
                            //-1 for every turn to the left
float angle;                // Angle between robot's present direction and the original one

void mapping_init() {
    //start counting steps.
    *distance_register = malloc(32);
}

int* get_distance_register() {
    return distance_register;
}

int getX() {
    return distance_register * cos(angle);
}

int getY() {
    return distance_register * sin(angle);
}