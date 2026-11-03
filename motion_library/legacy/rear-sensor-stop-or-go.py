robot.stand()
if robot.rear_distance_m() < 1:
    robot.stand()
else:
    robot.backward(1)
