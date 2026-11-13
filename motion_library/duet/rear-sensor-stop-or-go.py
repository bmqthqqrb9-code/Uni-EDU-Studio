if duet.rear_distance_m() < 1:
    duet.stop()
else:
    duet.backward(1)
