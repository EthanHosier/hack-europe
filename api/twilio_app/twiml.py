"""TwiML builders for Twilio voice (Media Stream, Say/Hangup)."""


def build_connect_stream_twiml(ws_url: str, call_sid: str, from_number: str, to_number: str) -> str:
    """TwiML that connects the call to a bidirectional Media Stream."""
    from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=ws_url)
    stream.parameter(name="CallSid", value=call_sid)
    stream.parameter(name="From", value=from_number)
    stream.parameter(name="To", value=to_number)
    connect.append(stream)
    response.append(connect)
    return response.to_xml()


def build_say_hangup_twiml(message: str) -> str:
    """TwiML that speaks a message and hangs up."""
    from twilio.twiml.voice_response import VoiceResponse

    response = VoiceResponse()
    response.say(message, voice="alice")
    response.hangup()
    return response.to_xml()
