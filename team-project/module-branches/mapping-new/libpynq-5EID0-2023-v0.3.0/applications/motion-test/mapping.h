#ifndef mapping
#define mapping

#include <libpynq.h>

void map_init(void);
void map_reset(void);
void map_update(int left_steps, int right_steps);
//int* get_distance_register(void);
float getX(void);
float getY(void);

#endif