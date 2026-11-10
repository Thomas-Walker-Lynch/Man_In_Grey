/*
  Man_In_Grey_gate·smoke - the gate of the smoke test's instruction language: the general
  gate with the language name and the guard's and interpreter's paths fixed.
*/
#include "Gate.lib.c"

int main(int argc ,char **argv){
  return Man_In_Grey_gate·Gate·run("smoke" ,"../Man_In_Grey/Smoke·Guard.py" ,"../Man_In_Grey/Smoke·Interpreter.py" ,argc ,argv);
}
