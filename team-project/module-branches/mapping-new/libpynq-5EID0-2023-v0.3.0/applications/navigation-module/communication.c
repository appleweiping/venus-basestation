#include "communication.h"
#include <libpynq.h>

//CONFIGURATION
#define ROBOT_ID 'A'


static void send_message_uart(const char *payload) {
    uint32_t length = strlen(payload);

    printf("Payload length: %u bytes\n", length);
    printf("Payload: %s\n", payload);

    // Send 4-byte payload length
    for (uint32_t i = 0; i < sizeof(length); i++) {
        uart_send(UART0, ((uint8_t *)&length)[i]);
    }

    // Send payload bytes
    for (uint32_t i = 0; i < length; i++) {
        uart_send(UART0, (uint8_t)payload[i]);
    }

    printf("UART message sent.\n");
}

void position_update(int x, int y, int angle) {
    char payload[128];
    const char robot_id = ROBOT_ID;
    snprintf(payload, sizeof(payload),
             "{\"robot_id\":\"%s\","
             "\"type\":\"position_update\","
             "\"x\":%d,"
             "\"y\":%d,"
             "\"heading\":%d}",
             robot_id, x, y, angle);

    send_message_uart(payload);
}

void communication_init() {
    switchbox_set_pin(IO_AR0, SWB_UART0_RX);
    switchbox_set_pin(IO_AR1, SWB_UART0_TX);

    uart_init(UART0);
}

void communication_destroy() {
    uart_destroy(UART0);
}
