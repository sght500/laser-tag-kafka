bullets = [1, 2, 3, 4]
for bullet in bullets[:]:  # Iterate over a copy
    if bullet % 2 == 1:
        bullets.remove(bullet)
print(bullets)
