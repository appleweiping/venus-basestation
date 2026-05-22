#ifndef TCS3200_H
#define TCS3200_H

/* ─── Color return values ─────────────────────────────────────────────────── */
/*
 * These are the possible return values of get_color().
 * Using #define constants means you can write:
 *
 *   if (get_color() == COLOR_RED) { ... }
 *
 * instead of having to remember which number means what.
 */
#define COLOR_WHITE   0
#define COLOR_BLUE    1
#define COLOR_GREEN   2
#define COLOR_BLACK   3
#define COLOR_RED     4
#define COLOR_UNKNOWN -1

/* ─── Public API ──────────────────────────────────────────────────────────── */

/*
 * init_color_sensor()
 *
 * Sets up GPIO pins and frequency scaling.
 * MUST be called once before using get_color().
 * Call after pynq_init().
 *
 * Returns: 1 on success, 0 on failure.
 */
int init_color_sensor(void);

/*
 * get_color()
 *
 * Reads all three color channels and returns the detected color.
 *
 * Returns one of:
 *   COLOR_WHITE   (0)
 *   COLOR_BLUE    (1)
 *   COLOR_GREEN   (2)
 *   COLOR_BLACK   (3)
 *   COLOR_RED     (4)
 *   COLOR_UNKNOWN (-1)  — when the reading doesn't match any known color
 */
const char* get_color(void);

/*
 * destroy_color_sensor()
 *
 * Cleans up any resources used by the color sensor.
 * Call before pynq_destroy().
 */
void destroy_color_sensor(void);
int read_color(int s1, int s2);

#endif /* TCS3200_H */