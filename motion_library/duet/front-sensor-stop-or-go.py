if duet.front_distance_m() < 1:
    duet.stop()
else:
    duet.walk(1)
