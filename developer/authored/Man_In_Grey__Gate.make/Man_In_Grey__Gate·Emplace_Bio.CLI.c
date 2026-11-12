/*
  Man_In_Grey__Gate·Emplace_Bio - the gate of the Emplace_Bio instruction
  language: the general gate with the language name and the guard's and
  interpreter's paths fixed.
*/
#include "Gate.lib.c"

int main(int argc ,char **argv){
  return Man_In_Grey__Gate·Gate·run("Emplace_Bio" ,"../Man_In_Grey/Emplace_Bio·Guard.py"
                                    ,"../Man_In_Grey/Emplace_Bio·Interpreter.py" ,argc ,argv);
}
