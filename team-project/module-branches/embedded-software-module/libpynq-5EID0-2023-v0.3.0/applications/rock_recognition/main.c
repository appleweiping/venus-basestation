#include <libpynq.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stepper.h>

#include "../distance_sensor/vl53l0x.h"

#define DETECT_DISTANCE_MM    130
#define CRUISE_SPEED          12000  

#define STEP_INCREMENT        1600    
#define BIG_STEP_STEPS        800   
#define SCAN_DELAY_MS         200

typedef enum {
    RESULT_SMALL_ROCK,
    RESULT_BIG_ROCK,
    RESULT_MOUNTAIN
} ObstacleVerdict;

ObstacleVerdict analyze_obstacle_size(int initial_distance) {
    printf("[Analyzer] Obstacle detected at %d mm. Commencing size analysis...\n", initial_distance);
    
    while (!stepper_steps_done()); 
    sleep_msec(500); 

    // --- PHASE 1 ---
    printf("[Analyzer] Taking big step forward to test for Small Rock...\n");
    stepper_steps(BIG_STEP_STEPS, BIG_STEP_STEPS);
    while (!stepper_steps_done());
    sleep_msec(SCAN_DELAY_MS); 

    int distance = get_distance();
    printf("[Analyzer] Scan 1 distance: %d mm\n", distance);

    if (distance == -1 || distance >= DETECT_DISTANCE_MM) {
        return RESULT_SMALL_ROCK;
    }

    // --- PHASE 2 ---
    printf("[Analyzer] Still blocked. Taking a second big step to test for Big Rock...\n");
    stepper_steps(BIG_STEP_STEPS, BIG_STEP_STEPS);
    while (!stepper_steps_done());
    sleep_msec(SCAN_DELAY_MS);

    distance = get_distance();
    printf("[Analyzer] Scan 2 distance: %d mm\n", distance);

    if (distance == -1 || distance >= DETECT_DISTANCE_MM) {
        return RESULT_BIG_ROCK;
    }

    // --- PHASE 3 ---
    return RESULT_MOUNTAIN;
}

int main(void) {
    pynq_init();

    printf("Initializing distance sensor...\n");
    if (init_distance_sensor() == 0) {
        printf("ERROR: Distance sensor initialization failed!\n");
        pynq_destroy();
        return EXIT_FAILURE;
    }
    
    sleep_msec(500); 

    stepper_init();
    stepper_enable();
    stepper_set_speed(CRUISE_SPEED, CRUISE_SPEED);
    printf("Motors ready. Walking forward continuously...\n");

    int print_counter = 0; // Added counter to prevent terminal spam

    while (1) {
        if (stepper_steps_done()) {
            stepper_steps(STEP_INCREMENT, STEP_INCREMENT);
        }

        int current_distance = get_distance();
        
        // DEBUG PRINT: Print the distance every ~500ms (10 loops * 50ms)
        if (print_counter++ % 10 == 0) {
            printf("DEBUG - Current sensor reading: %d mm\n", current_distance);
        }
        
        // Trigger condition
        if (current_distance != -1 && current_distance < DETECT_DISTANCE_MM) {
            
            ObstacleVerdict verdict = analyze_obstacle_size(current_distance);
            
            if (verdict == RESULT_SMALL_ROCK) {
                printf("FINAL VERDICT: It was a Small Rock. Resuming cruise...\n");
            } 
            else if (verdict == RESULT_BIG_ROCK) {
                printf("FINAL VERDICT: It was a Big Rock. Resuming cruise...\n");
            } 
            else if (verdict == RESULT_MOUNTAIN) {
                printf("FINAL VERDICT: Mountain ahead! Stopping.\n");
                break; 
            }
            
            stepper_set_speed(CRUISE_SPEED, CRUISE_SPEED);
        }

        sleep_msec(50); 
    }

    stepper_destroy();
    destroy_distance_sensor();
    pynq_destroy();
    return EXIT_SUCCESS;
}