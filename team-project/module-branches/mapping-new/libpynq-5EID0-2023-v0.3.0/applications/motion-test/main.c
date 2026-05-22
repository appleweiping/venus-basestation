#include <libpynq.h>
#include <stepper.h>

#include "mapping.h"


// void move(int distance_in_cm) {
//     float left,right;

//     left = distance_in_cm * ratio;
//     right = left;

//     if (steps <= 32767 && steps >= -32768) {
//     stepper_steps((int16_t)left, (int16_t)right);
//     while(!stepper_steps_done()) continue;
// }

//     sleep_msec(100);
// }

void move(int left ,int right) {

  stepper_steps(left, right);

  while(!stepper_steps_done()) continue;
  
  map_update(left, right);
  sleep_msec(10);
}

int main(void) {
  pynq_init();
  map_init();

  stepper_init();
  stepper_enable();
  stepper_set_speed(10000, 10000);

  

  move(1600, 1600);
  move(1000, -1000);
  move(500, 500);

  // stepper_steps(2513.08900, -2513.08900);

  // while(!stepper_steps_done()) continue;
  
  // map_update(2513.08900, -2513.08900);

  //printf("X is %f \n Y is %f\n", getX, getY);

  pynq_destroy();
  return EXIT_SUCCESS;
}