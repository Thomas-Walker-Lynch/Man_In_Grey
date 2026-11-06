/*
  Man_In_Grey_file_gate - the gate of the file instruction language: the general
  gate with its guard's name and the guard's and interpreter's paths fixed.
*/
#include "Gate.lib.c"

int main(int argc ,char **argv){
  return Man_In_Grey_gate·Gate·run("file" ,"../Man_In_Grey/guard_file.py" ,"../Man_In_Grey/interpreter_file.py" ,argc ,argv);
}
