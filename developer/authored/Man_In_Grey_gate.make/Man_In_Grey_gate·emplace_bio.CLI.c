/*
  Man_In_Grey_gate·emplace_bio - the gate of the emplace_bio instruction
  language: the general gate with the language name and the guard's and
  interpreter's paths fixed.
*/
#include "Gate.lib.c"

int main(int argc ,char **argv){
  return Man_In_Grey_gate·Gate·run("emplace_bio" ,"../Man_In_Grey/EmplaceBio·Guard.py"
                                   ,"../Man_In_Grey/EmplaceBio·Interpreter.py" ,argc ,argv);
}
