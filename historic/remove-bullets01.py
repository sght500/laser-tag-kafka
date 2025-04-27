bullets = [1, 2, 3, 4]
for bullet in bullets:
    if bullet % 2 == 1:  # Remove odd bullets
        bullets.remove(bullet)
print(bullets)
