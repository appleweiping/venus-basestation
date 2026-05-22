#include <stdio.h>
#include <libpynq.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* ─── Pin mapping ─────────────────────────────────────────────────────────── */
#define S0  IO_AR0
#define S1  IO_AR1
#define S2  IO_AR2
#define S3  IO_AR3
#define OUT IO_AR4

/* ─── Tuning constants ────────────────────────────────────────────────────── */

/*
 * At longer distances the return signal is much weaker.
 * A longer settle time prevents the previous filter bleeding into the next.
 */
#define FILTER_SETTLE_MS   300

/*
 * Longer count window accumulates more pulses on a weak signal,
 * giving a more stable reading.
 */
#define COUNT_WINDOW_MS    800

/*
 * Number of readings to average per channel.
 * Higher = more stable but slower per cycle.
 */
#define AVERAGE_SAMPLES    3

/*
 * Minimum dominance margin for colour classification (normalised 0–1).
 * At distance, readings are noisier so a larger margin avoids false calls.
 */
#define DOMINANCE_MARGIN   0.18f

/* ─── Calibration data ────────────────────────────────────────────────────── */

typedef struct {
    int r_min, r_max;
    int g_min, g_max;
    int b_min, b_max;
    int c_min, c_max;
} CalibrationData;

static CalibrationData cal;

/* ─── Filter selection ────────────────────────────────────────────────────── */

static void select_red(void) {
    gpio_set_level(S2, GPIO_LEVEL_LOW);
    gpio_set_level(S3, GPIO_LEVEL_LOW);
}

static void select_blue(void) {
    gpio_set_level(S2, GPIO_LEVEL_LOW);
    gpio_set_level(S3, GPIO_LEVEL_HIGH);
}

static void select_clear(void) {
    gpio_set_level(S2, GPIO_LEVEL_HIGH);
    gpio_set_level(S3, GPIO_LEVEL_LOW);
}

static void select_green(void) {
    gpio_set_level(S2, GPIO_LEVEL_HIGH);
    gpio_set_level(S3, GPIO_LEVEL_HIGH);
}

/* ─── Pulse counting ──────────────────────────────────────────────────────── */

/*
 * Count rising edges on OUT for `duration_ms` milliseconds.
 * The inner loop is kept as tight as possible to avoid missing pulses.
 */
static int count_pulses(int duration_ms) {
    int count = 0;

    struct timespec start, now;
    clock_gettime(CLOCK_MONOTONIC, &start);

    gpio_level_t prev = gpio_get_level(OUT);

    while (1) {
        gpio_level_t curr = gpio_get_level(OUT);

        if (prev == GPIO_LEVEL_LOW && curr == GPIO_LEVEL_HIGH) {
            count++;
        }
        prev = curr;

        /* Check elapsed time every 256 iterations to keep inner loop tight */
        if ((count & 0xFF) == 0) {
            clock_gettime(CLOCK_MONOTONIC, &now);
            long elapsed_ms =
                (now.tv_sec  - start.tv_sec)  * 1000L +
                (now.tv_nsec - start.tv_nsec) / 1000000L;
            if (elapsed_ms >= duration_ms) break;
        }
    }

    return count;
}

/* ─── Averaged channel read ───────────────────────────────────────────────── */

/*
 * Read a single channel AVERAGE_SAMPLES times and return the average.
 * This significantly reduces noise from the weaker signal at longer distances.
 */
static int read_channel_averaged(void (*select_fn)(void)) {
    select_fn();
    sleep_msec(FILTER_SETTLE_MS);

    long total = 0;
    for (int i = 0; i < AVERAGE_SAMPLES; i++) {
        total += count_pulses(COUNT_WINDOW_MS);
    }

    return (int)(total / AVERAGE_SAMPLES);
}

static int read_red(void)   { return read_channel_averaged(select_red);   }
static int read_green(void) { return read_channel_averaged(select_green); }
static int read_blue(void)  { return read_channel_averaged(select_blue);  }
static int read_clear(void) { return read_channel_averaged(select_clear); }

/* ─── Normalisation ───────────────────────────────────────────────────────── */

static float normalise(int raw, int min_val, int max_val) {
    if (max_val <= min_val) return 0.0f;
    float n = (float)(raw - min_val) / (float)(max_val - min_val);
    if (n < 0.0f) n = 0.0f;
    if (n > 1.0f) n = 1.0f;
    return n;
}

/* ─── Colour detection ────────────────────────────────────────────────────── */

static const char *detect_color(float r, float g, float b, float c) {
    /* No meaningful signal — likely out of range or no object present */
    if (c < 0.05f) {
        return "NO SIGNAL / TOO FAR";
    }

    /* Black: low reflectance across all channels */
    if (r < 0.15f && g < 0.15f && b < 0.15f) {
        return "BLACK";
    }

    /* White: high reflectance across all channels */
    if (r > 0.75f && g > 0.75f && b > 0.75f) {
        return "WHITE";
    }

    /* Dominant channel with margin to avoid misclassifying grey */
    if (r > g + DOMINANCE_MARGIN && r > b + DOMINANCE_MARGIN) return "RED";
    if (g > r + DOMINANCE_MARGIN && g > b + DOMINANCE_MARGIN) return "GREEN";
    if (b > r + DOMINANCE_MARGIN && b > g + DOMINANCE_MARGIN) return "BLUE";

    /* Mixed colours */
    if (r > 0.6f && g > 0.6f && b < 0.4f) return "YELLOW";
    if (r > 0.6f && b > 0.6f && g < 0.4f) return "MAGENTA";
    if (g > 0.6f && b > 0.6f && r < 0.4f) return "CYAN";

    return "UNKNOWN / GREY";
}

/* ─── Calibration ─────────────────────────────────────────────────────────── */

/*
 * IMPORTANT: Calibrate at the SAME distance you will use for detection.
 * Place the sensor at your target distance (e.g. 5 cm) for both steps.
 */
static void calibrate(void) {
    printf("=== CALIBRATION ===\n");
    printf("Place sensor at your target distance for both steps.\n\n");

    printf("Step 1: Point sensor at a WHITE surface, then press Enter.\n");
    fflush(stdout);
    getchar();

    printf("Reading WHITE reference (this takes a few seconds)...\n");
    fflush(stdout);
    cal.r_max = read_red();
    cal.g_max = read_green();
    cal.b_max = read_blue();
    cal.c_max = read_clear();
    printf("WHITE -> R:%d  G:%d  B:%d  C:%d\n\n",
           cal.r_max, cal.g_max, cal.b_max, cal.c_max);

    printf("Step 2: Point sensor at a BLACK surface (or cover it), then press Enter.\n");
    fflush(stdout);
    getchar();

    printf("Reading BLACK reference (this takes a few seconds)...\n");
    fflush(stdout);
    cal.r_min = read_red();
    cal.g_min = read_green();
    cal.b_min = read_blue();
    cal.c_min = read_clear();
    printf("BLACK -> R:%d  G:%d  B:%d  C:%d\n\n",
           cal.r_min, cal.g_min, cal.b_min, cal.c_min);

    /* Warn if white and black readings are too close — suggests poor signal */
    int c_range = cal.c_max - cal.c_min;
    if (c_range < 20) {
        printf("WARNING: Very low signal range (clear range = %d).\n", c_range);
        printf("Consider:\n");
        printf("  - Adding a brighter external LED aimed at the target\n");
        printf("  - Using a tube/baffle to block ambient light\n");
        printf("  - Reducing distance slightly\n\n");
    }

    printf("Calibration complete.\n\n");
    fflush(stdout);
}

/* ─── Main ────────────────────────────────────────────────────────────────── */

int main(void) {
    pynq_init();

    printf("TCS3200 — long-distance mode\n\n");
    printf("Wiring:\n");
    printf("  S0  -> IO_AR0 (A0)\n");
    printf("  S1  -> IO_AR1 (A1)\n");
    printf("  S2  -> IO_AR2 (A2)\n");
    printf("  S3  -> IO_AR3 (A3)\n");
    printf("  OUT -> IO_AR4 (A4)\n");
    printf("  VCC -> 3V3\n");
    printf("  GND -> GND\n");
    printf("  OE  -> GND  (if present)\n\n");
    fflush(stdout);

    /* GPIO setup */
    gpio_set_direction(S0,  GPIO_DIR_OUTPUT);
    gpio_set_direction(S1,  GPIO_DIR_OUTPUT);
    gpio_set_direction(S2,  GPIO_DIR_OUTPUT);
    gpio_set_direction(S3,  GPIO_DIR_OUTPUT);
    gpio_set_direction(OUT, GPIO_DIR_INPUT);

    /*
     * 100% frequency scaling: S0=HIGH, S1=HIGH
     *
     * At longer distances the return signal is weak.
     * 100% scaling gives the highest output frequency for a given light level,
     * making it much easier to count pulses from a dim return signal.
     *
     * If readings saturate (max counts even on dark surfaces) drop to 20%:
     *   gpio_set_level(S0, GPIO_LEVEL_HIGH);
     *   gpio_set_level(S1, GPIO_LEVEL_LOW);
     */
    gpio_set_level(S0, GPIO_LEVEL_HIGH);
    gpio_set_level(S1, GPIO_LEVEL_HIGH);
    printf("Frequency scaling: 100%%\n\n");
    fflush(stdout);

    /* Calibrate at the target distance before sensing */
    calibrate();

    /* Main sensing loop */
    while (1) {
        int raw_r = read_red();
        int raw_g = read_green();
        int raw_b = read_blue();
        int raw_c = read_clear();

        float nr = normalise(raw_r, cal.r_min, cal.r_max);
        float ng = normalise(raw_g, cal.g_min, cal.g_max);
        float nb = normalise(raw_b, cal.b_min, cal.b_max);
        float nc = normalise(raw_c, cal.c_min, cal.c_max);

        const char *detected = detect_color(nr, ng, nb, nc);

        printf("RAW   R:%-5d G:%-5d B:%-5d C:%-5d\n",
               raw_r, raw_g, raw_b, raw_c);
        printf("NORM  R:%.2f  G:%.2f  B:%.2f  C:%.2f  =>  %s\n\n",
               nr, ng, nb, nc, detected);
        fflush(stdout);

        sleep_msec(200);
    }

    pynq_destroy();
    return EXIT_SUCCESS;

#define S0  IO_A0
#define S1  IO_A1
#define S2  IO_A2
#define S3  IO_A3
#define OUT IO_A4

int read_color(int s2, int s3)
{
    gpio_set_level(S2, s2);
    gpio_set_level(S3, s3);

    sleep_msec(50);

    int count = 0;
    int last = gpio_get_level(OUT);

    for (int i = 0; i < 50000; i++)
    {
        int now = gpio_get_level(OUT);

        if (now != last)
        {
            count++;
            last = now;
        }
    }

    return count;
}

const char* decide_color(int r, int g, int b)
{
    // WHITE (everything high)
    if (r > 3000 && g > 2000 && b > 3000)
        return "WHITE";

    // GREEN (your strongest G range)
    if (g >= 1200)
        return "GREEN";

    // BLUE (medium G range)
    if (g >= 1080 && g <= 1180)
        return "BLUE";

    // RED (lowest G range)
    if (g >= 860 && g <= 910)
        return "RED";

    // BLACK / DARK
    if (r < 1500 && g < 1000 && b < 1500)
        return "BLACK";

    return "UNKNOWN";
}

int main(void)
{
    pynq_init();
    gpio_init();

    gpio_set_direction(S0, GPIO_DIR_OUTPUT);
    gpio_set_direction(S1, GPIO_DIR_OUTPUT);
    gpio_set_direction(S2, GPIO_DIR_OUTPUT);
    gpio_set_direction(S3, GPIO_DIR_OUTPUT);
    gpio_set_direction(OUT, GPIO_DIR_INPUT);

    gpio_set_level(S0, 1);
    gpio_set_level(S1, 1);

    while (1)
    {
        int red = read_color(0, 0);
        int blue = read_color(0, 1);
        int green = read_color(1, 1);

        const char* color = decide_color(red, green, blue);

        printf("R:%d G:%d B:%d -> %s\n", red, green, blue, color);

        sleep_msec(500);
    }

    pynq_destroy();
    return 0;
}
}