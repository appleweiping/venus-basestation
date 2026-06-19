#ifndef communication_h
#define communincation_h

#include <libpynq.h>

void communication_init(void);
void send_position_update(float x, float y, float angle);
void send_block_found(float x, float y, char *color, int size);
void send_border_found(float x, float y);
void send_mountain_found(float x, float y);
void send_cliff_found(float x, float y);
void communication_destroy(void);

#endif