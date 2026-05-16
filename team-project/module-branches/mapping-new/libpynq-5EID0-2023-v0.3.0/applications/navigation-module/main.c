#include <libpynq.h>
#include "motion-functions.h"
#include "mapping.h"

void init() {
  pynq_init();
  mapping_init();
  motionInit(50, get_distance_register());
}

void destroy() {
  motionDestroy();
  pynq_destroy();
}

//TODO
/*
  - obsticle();
  - approaching_mate();
  - analyze();
  - sendOut();
  - orient(); -> motion-functions.c

  - Write pseudo-code for option 2
*/

//See design document 2.4.2 (pg. 6)
void option1() { 
  while ((!obsticle) && (!approaching_mate)) {
      move(3);
    }


    sample_data_t data = analyze();

    send_sample_data(data);
    send_location_data(getX(), getY());

    
    turn90(RIGHT);
  
}

void option2() {
  while(!border) {
    option1();
  }

  orient();
  
}

int main(void) {
  init();

  while(true) {
    option1();
  }

  
  destroy();
  return EXIT_SUCCESS;
}

