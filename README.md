# Snake game

#### Simple explanation of the game
1. Each player control their snake.
2. It can eat apple, one apple == one point.
3. The user who get highest score wins the game.

#### Network key function
1. provide synchronized game space to users who are in the same server
   they can check real-time top score
2. exception (latency, packet loss, go out of network, ... etc)
3. MultiServer (user can choose the server, maybe it have difference of map, each map is share same server)
4. each server construct seperately, but after synchronize (maybe globally highest score?)

#### Interface concept
![image](https://github.com/user-attachments/assets/0517e43e-92bd-4ef3-b129-a706521b89dd)
![image](https://github.com/user-attachments/assets/95bb805f-71ba-407d-88fc-5e20f860cba1)
![image](https://github.com/user-attachments/assets/6e64d75c-7eef-4d0e-9a38-d196ec31fee0)
