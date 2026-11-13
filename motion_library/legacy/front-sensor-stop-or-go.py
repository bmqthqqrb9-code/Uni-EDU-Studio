robot.stand()
if robot.front_distance_m() < 1:
    robot.stand()
else:
    robot.walk(1)
