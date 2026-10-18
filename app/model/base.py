from abc import ABC, abstractmethod

class Model(ABC):


    @abstractmethod
    def transcribe(self, audio_path):
        pass

    @abstractmethod
    def status(self):
        pass