#include <libpynq.h>
#include "communication.h"

int main(void) {
    pynq_init();

    communication_init();
    send_mountain_found(0.32, 0.78);

    communication_destroy();
    pynq_destroy();

    return 0;
}
