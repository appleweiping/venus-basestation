#include <libpynq.h>
#include "VL53L0X.h"
#include "tmprtr_v0.2.h"
#include "tcs3200.h"

void sensors_init() {
  init_color_sensor();
  distance_init();
  temperature_init();
}

void sensors_destroy() {
  distance_destroy();
  temperature_destroy();
}

int main(void) {
  pynq_init();
  sensors_init();
  
  while(1) {
    
    // printf("Color: %s\n", get_color());
    //printf("Distance: %d\n", getDistance());
    printf("RGB: R %d, G %d, B %d --> %s \n", read_color(0,0), read_color(0,1), read_color(1,1), get_color());
    //printf("Temperature: %f\n", getTemperature());

    
    sleep_msec(1000);
  }
  
  sensors_destroy();
  pynq_destroy();
  return EXIT_SUCCESS;
}
