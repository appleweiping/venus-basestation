#include "algorithm-options.h"
#include <libpynq.h>
/*IN THE WORKS*/
void option1() { 
  while ((!obsticle) && (!approaching_mate)) {
      move(3);
    }
    
    
    sample_data_t data = analyze();

    send_sample_data(data);
    


    turn90(RIGHT);
  
}

void option2() {
  while(!border) {
    option1();
  }

  orient();
  
}
