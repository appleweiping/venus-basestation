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

void send_position_update(float x, float y, float angle) {
    char payload[128];
    const char *robot_id = "A";
    snprintf(payload, sizeof(payload),
             "{\"robot_id\":\"%s\","
             "\"type\":\"position_update\","
             "\"x\":%.2f,"
             "\"y\":%.2f,"
             "\"heading\":%.2f}",
             robot_id, x, y, angle);

    send_message_uart(payload);
}

void send_block_found(float x, float y, char* color, int size) {
    char payload[128];
    const char *robot_id = "A";
    snprintf(payload, sizeof(payload),
             "{\"robot_id\":\"%s\","
             "\"type\":\"block_found\","
             "\"x\":%.2f,"
             "\"y\":%.2f,"
             "\"color\":\"%s\","
             "\"size\":%d}",
             robot_id, x, y, color, size);

    send_message_uart(payload);
}

void send_border_found(float x, float y) {
    char payload[128];
    const char *robot_id = "A";
    snprintf(payload, sizeof(payload),
             "{\"robot_id\":\"%s\","
             "\"type\":\"border_found\","
             "\"x\":%.2f,"
             "\"y\":%.2f}",
             robot_id, x, y);

    send_message_uart(payload);
}

void send_mountain_found(float x, float y) {
    char payload[128];
    const char *robot_id = "A";
    snprintf(payload, sizeof(payload),
             "{\"robot_id\":\"%s\","
             "\"type\":\"mountain_found\","
             "\"x\":%.2f,"
             "\"y\":%.2f}",
             robot_id, x, y);

    send_message_uart(payload);
}

void send_cliff_found(float x, float y) {
    char payload[128];
    const char *robot_id = "A";
    snprintf(payload, sizeof(payload),
             "{\"robot_id\":\"%s\","
             "\"type\":\"cliff_found\","
             "\"x\":%.2f,"
             "\"y\":%.2f}",
             robot_id, x, y);

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
