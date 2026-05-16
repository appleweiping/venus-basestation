#include <libpynq.h>
#include "motion-functions.h"
#include "motion-functions.c"


int main(void) {
  pynq_init();
  motionInit(50);
  move(10);
  pynq_destroy();
  return EXIT_SUCCESS;
}