#include <libpynq.h>
#include "motion-functions.h"
#include "mapping.h"
#include "communication.h"
#include "algorithm-options.h"
#include "sensor-handlers.h"
#include "tcs3200.h"   // gives you get_color() and the COLOR_* constants

void init() {
  pynq_init();
  mapping_init();
  communication_init();
  options_init();
  motionInit(50);
  init_color_sensor();
}

void destroy() {
  motionDestroy();
  pynq_destroy();
}

/* BLOCKING FUNCTIONS 


  move(); - 100msec

*/

//TODO
/*
  - obsticle();
  - approaching_mate();
  - analyze();
  - sendOut();
  - orient(); -> motion-functions.c

  - Write pseudo-code for option 2
*/

/*
  FOR COMMUNICATION

    - make a communication.c
    - make a communication.h

    - create an init function that starts the stuff

    We could also start the mqqt handler on startup without the need of the main program

    

*/

void option1() { 
  
  
}

//See design document 2.4.2 (pg. 6)

int main(void) {
  init();

  while(true) {
    option1();
    

  }
  
  destroy();
  return EXIT_SUCCESS;
}

