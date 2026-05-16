#include <libpynq.h>

void init() {
  pynq_init();
  motionInit(50);
}

void destroy() {
  motionDestroy();
  pynq_destroy();
}

int main(void) {
  init();

  move(10);

  move(10);
  
  destroy();
  return EXIT_SUCCESS;
}
