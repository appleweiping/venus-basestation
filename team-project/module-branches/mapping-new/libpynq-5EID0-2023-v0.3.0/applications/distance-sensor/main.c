#include <libpynq.h>
#include "VL53L0X.h"

int main(void) {

  pynq_init();
  distance_init();

  while (1) {
    printf("[MAIN] distance: %u mm\n", getDistance());
    sleep_msec(1000);
  }

  distance_destroy();
  pynq_destroy();
  return EXIT_SUCCESS;
}
