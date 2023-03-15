import matplotlib.pyplot as plt
import numpy as np
with open('Ciclo_Prueba.txt') as f:
    data = f.read()
data = data.split('\n')
data.pop(0)
enviado = data[::2]
recibido = data[1::2]

for i,e in enumerate(enviado):
    enviado[i] = float(e.replace('Enviado :',''))
for i,r in enumerate(recibido):
    recibido[i] = float(r.replace('Recibido :',''))

tiempo = np.arange(0,len(enviado)/2,0.5)

plt.plot(tiempo,enviado,label='Enviado')
plt.plot(tiempo,recibido,label='Recibido')
plt.legend()
plt.xlabel('Tiempo [s]')
plt.ylabel('Señal recibida (255 = 100%)')
plt.title('Filtrado de la señal pwm')
plt.show()
