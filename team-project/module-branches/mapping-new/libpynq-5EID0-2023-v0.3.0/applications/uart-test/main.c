#include <libpynq.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

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

int main(void) {
    pynq_init();

    // Route AR0 and AR1 to UART0
    switchbox_set_pin(IO_AR0, SWB_UART0_RX);
    switchbox_set_pin(IO_AR1, SWB_UART0_TX);

    uart_init(UART0);

    const char *payload =
        "{\"robot_id\":\"A\","
        "\"type\":\"position_update\","
        "\"x\":3,"
        "\"y\":5,"
        "\"heading\":90}";

    send_message_uart(payload);

    uart_destroy(UART0);
    pynq_destroy();

    return 0;
}