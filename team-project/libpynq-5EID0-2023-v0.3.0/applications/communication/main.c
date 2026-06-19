#include <libpynq.h>
#include "communication.h"

int main(void) {
    pynq_init();
    
    communication_init();
    while (true) {
        send_position_update(1.23, 4.56, 90.0);
        send_block_found(2.34, 5.67, "Red", 1);
        send_border_found(3.45, 6.78);
        send_mountain_found(0.32, 0.78);
        send_cliff_found(4.56, 7.89);

        sleep_msec(1000);
    }
    communication_destroy();
    pynq_destroy();

    return 0;
}