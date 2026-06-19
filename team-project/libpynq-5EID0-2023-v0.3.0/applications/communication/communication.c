#include "communication.h"
#include <libpynq.h>
#include <json-c/json.h>
#include <json-c/json_object.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>

// CONFIGURATION
#define ROBOT_ID "A"

// Helper function to force 2 decimal places for doubles in JSON string
static json_object* create_formatted_double(float value) {
    json_object *j_val = json_object_new_double(value);
    // Force the serializer to output with exactly two decimals
    json_object_set_serializer(j_val, json_object_double_to_json_string, "%.2f", NULL);
    return j_val;
}

// Helper function to write to UART
static void uart_write_array(const int uart, uint8_t *buf, uint32_t l) {
    for (uint32_t x = 0; x < l; x++) {
        uart_send(uart, buf[x]);
    }
}

// Handles length prepending, array writing, and transmission sleep
static void send_message_uart(const char *payload) {
    uint32_t size = strlen(payload);

    printf("Payload length: %u bytes\n", size);
    printf("Payload: %s\n", payload);

    // Send 4-byte payload length
    uart_write_array(UART0, (uint8_t *)&size, 4);

    // Send payload bytes
    uart_write_array(UART0, (uint8_t *)payload, size);

    // Sleep to allow transmission to complete
    sleep_msec(size * 2); 

    printf("UART message sent.\n");
}

void send_position_update(float x, float y, float angle) {
    json_object *jobj = json_object_new_object();
    
    json_object_object_add(jobj, "robot_id", json_object_new_string(ROBOT_ID));
    json_object_object_add(jobj, "type", json_object_new_string("position_update"));
    json_object_object_add(jobj, "x", create_formatted_double(x));
    json_object_object_add(jobj, "y", create_formatted_double(y));
    json_object_object_add(jobj, "heading", create_formatted_double(angle));

    const char *json_string = json_object_to_json_string(jobj);
    send_message_uart(json_string);
    
    json_object_put(jobj);
}

void send_block_found(float x, float y, char* color, int size) {
    json_object *jobj = json_object_new_object();
    
    json_object_object_add(jobj, "robot_id", json_object_new_string(ROBOT_ID));
    json_object_object_add(jobj, "type", json_object_new_string("block_found"));
    json_object_object_add(jobj, "x", create_formatted_double(x));
    json_object_object_add(jobj, "y", create_formatted_double(y));
    json_object_object_add(jobj, "color", json_object_new_string(color));
    json_object_object_add(jobj, "size", json_object_new_int(size));

    const char *json_string = json_object_to_json_string(jobj);
    send_message_uart(json_string);
    
    json_object_put(jobj);
}

void send_border_found(float x, float y) {
    json_object *jobj = json_object_new_object();
    
    json_object_object_add(jobj, "robot_id", json_object_new_string(ROBOT_ID));
    json_object_object_add(jobj, "type", json_object_new_string("border_found"));
    json_object_object_add(jobj, "x", create_formatted_double(x));
    json_object_object_add(jobj, "y", create_formatted_double(y));

    const char *json_string = json_object_to_json_string(jobj);
    send_message_uart(json_string);
    
    json_object_put(jobj);
}

void send_mountain_found(float x, float y) {
    json_object *jobj = json_object_new_object();
    
    json_object_object_add(jobj, "robot_id", json_object_new_string(ROBOT_ID));
    json_object_object_add(jobj, "type", json_object_new_string("mountain_found"));
    json_object_object_add(jobj, "x", create_formatted_double(x));
    json_object_object_add(jobj, "y", create_formatted_double(y));

    const char *json_string = json_object_to_json_string(jobj);
    send_message_uart(json_string);
    
    json_object_put(jobj);
}

void send_cliff_found(float x, float y) {
    json_object *jobj = json_object_new_object();
    
    json_object_object_add(jobj, "robot_id", json_object_new_string(ROBOT_ID));
    json_object_object_add(jobj, "type", json_object_new_string("cliff_found"));
    json_object_object_add(jobj, "x", create_formatted_double(x));
    json_object_object_add(jobj, "y", create_formatted_double(y));

    const char *json_string = json_object_to_json_string(jobj);
    send_message_uart(json_string);
    
    json_object_put(jobj);
}

void communication_init() {
    switchbox_set_pin(IO_AR0, SWB_UART0_RX);
    switchbox_set_pin(IO_AR1, SWB_UART0_TX);

    uart_init(UART0);
    uart_reset_fifos(UART0);
}

void communication_destroy() {
    uart_destroy(UART0);
}