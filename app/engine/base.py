from abc import ABC, abstractmethod


class Engine(ABC):

    @abstractmethod
    def transcribe(self, audio_path):
        pass
    