from __future__ import print_function
import sys
import os
from PyQt4.QtCore import *
from PyQt4.QtGui  import *
from PyQt4 import QtSvg

from time import sleep
import numpy as np

from transform_action import pack_action


class QGraphicsViewExtend(QGraphicsView):
    """ extends QGraphicsView for resize event handling  """

    def __init__(self, parent=None):

        super(QGraphicsViewExtend, self).__init__(parent)               
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    
    def resizeEvent(self, event):

        self.fitInView(QRectF(0,0,1280,1080),Qt.KeepAspectRatio)
        # self.fitInView(QRectF(self.viewport().rect()),Qt.KeepAspectRatio)


class CardGraphicsItem(QtSvg.QGraphicsSvgItem):
    """ Extends Qt.QGraphicsItem for card items graphics """ 

    def __init__(self, card, svgFile, player, faceDown=False):

        super(CardGraphicsItem, self).__init__(svgFile)

        # special properties
        self.card = card        
        self.svgFile = svgFile # svg file for card graphics
        self.player = player # which player holds the card
        self.faceDown = faceDown # does the card faceDown
        self.anim = QPropertyAnimation(self, "pos") # will use to animate card movement
        self.clicked = False
        
        #default properties
        self.setAcceptHoverEvents(True) #by Qt default it is set to False                 


    def hoverEnterEvent(self, event):
        """ event when mouse enter a card """    

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(15)
        effect.setColor(Qt.red)        
        effect.setOffset(QPointF(-5,0))
        self.setGraphicsEffect(effect)        
    

    def hoverLeaveEvent(self, event):
        """ event when mouse leave a card """    

        if not self.clicked:

            self.setGraphicsEffect(None) 
    
    
#    def __repr__(self):                
#        return '<CardGraphicsItem: %d>' % self.card
     
        
class cardTableWidget(QWidget):
    """ main widget for handling the card table """

    def __init__(self, env, parent=None):

        self.env = env

        gameboard = env.gameboard

        self.p1_board = gameboard.p1_board
        self.p2_board = gameboard.p2_board

        self.p1_hand = self.p1_board.hand[:]
        self.p1_hand_graphics = []
        self.p2_hand = self.p2_board.hand[:]

        p1_played = [[], [], [], []]
        p2_played = [[], [], [], []]

        self.all_discarded = [[], [], [], []]

        self.all_played = [p1_played, p2_played]

        self.deck = gameboard.deck.deckofcards[:]

        self.p1_card_to_change = None
        self.p1_card_graphics_to_change = None
        self.p1_play = False
        self.p1_discard = False
        self.p1_card_to_draw = None
        self.p1_card_graphics_to_draw = None

        self.last_p1_card = None
        self.last_p1_card_z = None
        self.p1_hand_animated = False
        
        super(QWidget, self).__init__(parent)       

        self.initUI()

        
    def initUI(self):
        """ initialize the view-scene graphic environment """

        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 1920, 1080)

        self.view = QGraphicsViewExtend(self.scene)
        self.view.setSceneRect(QRectF(self.view.viewport().rect()))
        self.view.setSceneRect(QRectF(0, 0, 1920, 1080))
        self.view.setRenderHint(QPainter.Antialiasing)        

        layout = QGridLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)        
        self.setBackgroundColor(QColor('green'))

        # special properties
        self.svgCardsPath = "SVG"
        self.cardsGraphItems = [] #holds all the cards items
        self.defInsertionPos = QPointF(0,0)
        self.defAngle = 0
        self.scale = 0.3

        self.numOfPlayers = 2

        self.card_width = 691
        self.card_height = 1056

        deck_x = 10 + self.card_height * self.scale
        discard_y = 60

        self.defHandSpacing = 68
        self.playersHandsPos = [(380, 700, 0), (380, 50, 180)] #(x,y,angle)

        draw_offset = 990 / 4.
        self.discardPos = [(deck_x, discard_y, 90), (deck_x, discard_y + draw_offset, 90), (deck_x, discard_y + 2 * draw_offset, 90), (deck_x, discard_y + 3 * draw_offset, 90)]

        self.deckPos = (deck_x + 540, discard_y + 1.5 * draw_offset, 90)

        self.boardSpacing = 54
        p1_y = 580
        p2_y = 500 - self.card_height * self.scale
        suit_spacing = 220
        self.boardPos = [[(1100, p1_y, 0), (1100 + suit_spacing, p1_y, 0), (1100 + 2 * suit_spacing, p1_y, 0), (1100 + 3 * suit_spacing, p1_y, 0)], 
                [(1100, p2_y, 0), (1100 + suit_spacing, p2_y, 0), (1100 + 2 * suit_spacing, p2_y, 0), (1100 + 3 * suit_spacing, p2_y, 0)]]

        discard_rectF = QRectF(0, 40, 340, 1000)

        #pen = QPen("cyan")
        pen = QPen()
        #brush = QBrush("blue")
        brush = QBrush()
        self.scene.addRect(discard_rectF, pen, brush)
#        c = QtSvg.QGraphicsSvgItem('svg\j_b.svg')
#        c.setPos(0,0)
#        self.scene.addItem(c)

        self.discard_rect = QRegion(0, 40, 340, 1000)

        self.dealHands()
        self.dealDeck()

        # self.dealDiscards()

        # self.dealPlayed()
        # print(self.scene.itemAt(110,110))


    def process_non_card_click(self, p):

        print('clicked registered, but not on card')
        print('p1_card: ', self.p1_card_to_change)

        if ((self.p1_card_to_change != None)):

            if ((self.p1_play and self.p1_discard) == -1):

                to_discard = self.discard_rect.contains(p)
                print('Point inside of discard rectangle: ', to_discard)

                if (to_discard): 
                    self.p1_discard = 1
                    self.p1_play = 0

                else:

                    self.p1_discard = 0
                    self.p1_play = 1

            else:
                print('Play/discard already chosen. Resetting card...')
                self.p1_card_to_change = None


    def update_card_to_change(self, card_graphics):

        print('Not yet a card to play')

        card = card_graphics.card

        if (card in self.p1_hand):

            self.p1_card_to_change = card
            self.p1_card_graphics_to_change = card_graphics
            self.last_p1_card = card_graphics.pos()
            self.last_p1_card_z = card_graphics.zValue()

            print('Card pos: ', self.last_p1_card)
            print('Card z: ', self.last_p1_card_z)

        self.p1_play = -1
        self.p1_discard = -1
        self.p1_card_to_draw = None
        self.p1_card_graphics_to_draw = None


    def update_hand_card_action(self, card, suit):

        if (card in self.all_discarded[suit]):
            
            self.p1_discard = 1
            self.p1_play = 0

            self.p1_hand.remove(self.p1_card_to_change)

        else:

            if (self.p1_board.valid_play(card)):

                self.p1_discard = 0
                self.p1_play = 1

                self.p1_hand.remove(self.p1_card_to_change)

            else:

                print('')
                print('Invalid play requested. Resetting state...')
                print('')

                self.p1_play = -1
                self.p1_discard = -1
                self.p1_card_to_change = None
                self.p1_card_graphics_to_change = None
                self.last_p1_card = None
                self.last_p1_card_z = None


    def animate_hand_card(self):

        animate = False

        if (((self.p1_play and self.p1_discard) != -1) and (self.p1_hand_animated == False)):

            if animate:

                if (self.p1_discard == 1):
                    print('Discard action. Attempting to rotate...')
                    self.p1_card_graphics_to_change = self.rotate_card(self.p1_card_graphics_to_change, 1)

                    print('Last p1 card after rotation: ', self.last_p1_card)
                    sleep(0.1)

                print('Both play and discard recorded. Attempting to animate...')

                # animate move
                self.p1_card_graphics_to_change.anim.setDuration(15)

                end_pos = self.find_new_card_pos(self.p1_card_to_change, 0, self.p1_discard, 1)
                print('Desired end position: ', end_pos)

                print('Last p1 card before rotation: ', self.last_p1_card)

                self.p1_card_graphics_to_change.anim.setEndValue(end_pos)
                self.p1_card_graphics_to_change.anim.start() 

                print('Last p1 card after animation: ', self.last_p1_card)
                print('animation completed.')
                print('End position: ', self.p1_card_graphics_to_change.pos())

            else:

                if (self.p1_discard == 1):
                    print('Discard action. Attempting to rotate...')
                    self.p1_card_graphics_to_change = self.rotate_card(self.p1_card_graphics_to_change, 1)

                    print('Last p1 card after rotation: ', self.last_p1_card)

                end_pos = self.find_new_card_pos(self.p1_card_to_change, 0, self.p1_discard, 1)
                self.p1_card_graphics_to_change.setPos(end_pos)

            self.p1_hand_animated = True
            self.p1_card_graphics_to_change.clicked = False


    def process_draw_click(self, card_graphics):

        animate = False

        card = card_graphics.card

        if (card in self.deck):

            draw_int = 0

        else:

            suit = int(card / 13)

            draw_int = suit + 1

        self.p1_card_to_draw = card
        self.p1_card_graphics_to_draw = card_graphics

        print('Missing position for draw card: ', self.last_p1_card)

#        if animate:
#
#            if (draw_int == 0):
#                self.p1_card_graphics_to_draw = self.flip_card(self.p1_card_graphics_to_draw, 1, self.last_p1_card_z)
#
#            else:
#                self.p1_card_graphics_to_draw = self.unrotate_card(self.p1_card_graphics_to_draw, 1)
#
#            # animate move
#            self.p1_card_graphics_to_draw.anim.setDuration(15)
#
#            #self.p1_card_graphics_to_draw.anim.setStartValue(card_graphics.pos())
#            end_pos = self.find_new_card_pos(card, 1, 0, 1, self.last_p1_card)
#            print('end position for card drawn: ', end_pos)
#            self.p1_card_graphics_to_draw.anim.setEndValue(end_pos)
#            self.p1_card_graphics_to_draw.anim.start() 
#
#        else:
#
#            if (draw_int == 0):
#                self.p1_card_graphics_to_draw = self.flip_card(self.p1_card_graphics_to_draw, 1, self.last_p1_card_z)
#
#            else:
#                self.p1_card_graphics_to_draw = self.unrotate_card(self.p1_card_graphics_to_draw, 1)
#
#            self.p1_card_graphics_to_draw.setPos(self.last_p1_card)

        if (draw_int == 0):
            self.deck.remove(self.p1_card_to_draw)
        else:
            self.all_discarded[draw_int-1].remove(self.p1_card_to_draw)

        self.p1_card_graphics_to_draw.clicked = False

        print('animation completed.')

        action = pack_action(self.p1_card_to_change, self.p1_play, draw_int)
        print('Final action: ', action)

        return action


    def perform_step_from_click(self, action):

        # update lists
        print('card to change: ', self.p1_card_to_change)

        print('Length of p1_hand_graphics :', len(self.p1_hand_graphics))

        idx = 8

        for card_int in range(8):
            if (self.p1_hand[card_int] == self.p1_card_to_change):
                idx = card_int

        self.p1_hand[idx] = self.p1_card_to_draw
        self.p1_hand_graphics[idx] = self.p1_card_graphics_to_draw

        to_change_suit = int(self.p1_card_to_change / 13)

        if (self.p1_play == 1):
            self.all_played[0][to_change_suit].append(self.p1_card_to_change)
        else:
            self.all_discarded[to_change_suit].append(self.p1_card_to_change)

        self.redealHand()

        self.p1_play = -1
        self.p1_discard = -1
        self.p1_card_to_change = None
        self.p1_card_graphics_to_change = None
        self.p1_card_to_draw = None
        self.p1_card_graphics_to_draw = None
        self.last_p1_card = None
        self.last_p1_card_z = None
        self.p1_hand_animated = False

        self.env.step(action, 1)


    def process_click(self, card_graphics, card_clicked, p):

        if (not card_clicked):

            self.process_non_card_click(p)

            self.animate_hand_card()

        else:

            print('card clicked')

            card_graphics.clicked = True

            card = card_graphics.card
            suit = int(card / 13)

            # If there isn't yet a card to play, update the card to be played
            if (self.p1_card_to_change is None):
                self.update_card_to_change(card_graphics)

            else:

                print('Card already chosen')
                print('Last p1 card position: ', self.last_p1_card)

                # If we have not decided if we will play or discard yet, use
                # this click to make the distinction
                if ((self.p1_play and self.p1_discard) == -1):

                    self.update_hand_card_action(card, suit)

                else:

                    action = self.process_draw_click(card_graphics)

                    self.perform_step_from_click(action)

        self.animate_hand_card()

    
    def mousePressEvent(self, event):

        # check if item is a CardGraphicsItem  
        p = event.pos()
        #print(p)
        p -= QPoint(10,10) #correction to mouse click. not sure why this happen        
        itemAt = self.view.itemAt(p)       
        print('itemAt: ', itemAt)

        card_clicked = False

        if isinstance(itemAt, CardGraphicsItem):

            # Give the card a black outline
            effect = QGraphicsDropShadowEffect(itemAt)
            effect.setBlurRadius(15)
            effect.setColor(Qt.blue)        
            effect.setOffset(QPointF(-5,0))
            itemAt.setGraphicsEffect(effect)        

            card_clicked = True

        # Update figure out the correct action from the click
        self.process_click(itemAt, card_clicked, p)

        #print("All items at pos: ", end="")
        #print(self.view.items(p))

        #print("view.mapToScene: ",end="")
        #print(self.view.mapToScene(p))

        
    def find_new_card_pos(self, card, draw, discard, player, missing_hand_pos=None):

        if (player == 1):
            hand = self.p1_hand
        else:
            hand = self.p2_hand

        if (draw == 1):

            return self.find_new_card_pos_hand(player, missing_hand_pos)

        if (discard == 1):

            return self.find_new_card_pos_discard(card)

        return self.find_new_card_pos_play(card, player)


    def find_new_card_pos_discard(self, card):
        '''Finds postition of card to be discarded.'''

        suit = int(card / 13)

        (x_i, y_i, ang) = self.discardPos[suit]

        return QPointF(x_i, y_i)


    def find_new_card_pos_play(self, card, player=1):
        '''Finds postition of card to be played.'''

        suit = int(card / 13)

        (x_i, y_i, ang) = self.boardPos[player-1][suit]
        current_n_played_cards = len(self.all_played[player-1][suit])
        
        if (player == 1):
            dy = self.boardSpacing
        else:
            dy = -1 * self.boardSpacing

        x_f = x_i
        y_f = y_i + (current_n_played_cards + 1)

        return QPointF(x_f, y_f)


    def find_new_card_pos_hand(self, player, missing_hand_pos):
        '''Finds position of card to be added to hand.'''

        return missing_hand_pos

#        if (player == 1):
#            return self.last_p1_card
#
#        return self.last_p2_card


    def setBackgroundColor(self, color):
        """ add background color """
        
        brush = QBrush(color)
        self.scene.setBackgroundBrush(brush)
        self.scene.backgroundBrush() 


    def cardsvgFile(self, card):

        if (card == -1):
            name = 'blue_back'

        else:

            suit = int(card / 13)
            face_val = card % 13

            if (suit == 0):
                suit_str = 'C'
            elif (suit == 1):
                suit_str = 'D'
            elif (suit == 2):
                suit_str = 'H'
            elif (suit == 3):
                suit_str = 'S'

            if (face_val == 0):
                face_str = 'A'
            elif (face_val == 10):
                face_str = 'J'
            elif (face_val == 11):
                face_str = 'Q'
            elif (face_val == 12):
                face_str = 'K'
            else:
                face_str = str(face_val + 1)

            name = face_str + suit_str

        fn = os.path.join(self.svgCardsPath, name + ".svg")        
        return fn

            
    def addCard(self, card, player, faceDown=False):
        """ adds CardGraphicsItem graphics to board.
        also updates the total cards list
        """        
        # svg file of the card graphics
        if faceDown:
            svgFile = self.cardsvgFile(-1)
        else:
            svgFile = self.cardsvgFile(card)

        ind = len(self.getCardsList()) + 1

        # create CardGraphicsItem instance
        tmp = CardGraphicsItem(card, svgFile, player, faceDown)

        tmp.setScale(self.scale)
        tmp.setZValue(ind) # set ZValue as index (last in is up)        

        self.scene.addItem(tmp)

        return tmp
        

    def removeCard(self, card):
        """ removes CardGraphicsItem graphics from board 
        also removes from the total cards list
        """
        self.scene.removeItem(card)


    def changeCard(self, cardIndRemove, card, faceDown=False):       
        """ replace CardGraphicsItem         
        keeps same index and ZValue !
        """
        zValueTmp = self.cardsGraphItems[cardIndRemove].zValue()
        position = self.cardsGraphItems[cardIndRemove].pos()
        angle = self.cardsGraphItems[cardIndRemove].rotation()
        scale = self.cardsGraphItems[cardIndRemove].scale()
        self.scene.removeItem(self.cardsGraphItems[cardIndRemove])
        self.cardsGraphItems.pop(cardIndRemove)
        player = self.cardsList[cardIndRemove].player
        self.cardsList.pop(cardIndRemove)

        # svg file of the card graphics
        if faceDown:
            svgFile = self.cardSvgFile(-1)
        else:
            svgFile = self.cardSvgFile(card)

        ind = cardIndRemove
        self.cardsList.insert(ind,CardItem(card,self.value(card),player,faceDown))        
        tmp = CardGraphicsItem(card, ind, position, svgFile, angle, scale)
        tmp.setZValue(zValueTmp) # set ZValue as previous
        self.cardsGraphItems.insert(ind, tmp)
        self.scene.addItem(self.cardsGraphItems[ind])
        self.checkLists()


    def getCardsList(self):
        """ returns and prints all CardGraphicsItem in scene (disregard other graphics items) """        
        itemsOut=[]
        #print("Cards List:")
        for item in self.scene.items():
            if isinstance(item,CardGraphicsItem):                
                itemsOut.append(item)
                #print("Ind=%3d |card=%4s | Player=%d | faceDown=%r " % \
                #     (item.ind, item.card, item.player, item.faceDown) )                
        #print("Total cards num = " + str(len(itemsOut)))
        return itemsOut


    def redealHand(self):

        dx = self.defHandSpacing
        dy = 0

        x, y, ang = self.playersHandsPos[0]

        graphics = self.p1_hand_graphics[:]

        for card_graphic in graphics:
            self.removeCard(card_graphic)

        for offset in range(8):

            card = self.p1_hand[offset]

            faceDown = False

            card_graphics = self.addCard(card, 1, faceDown)
            self.getCardsList()[0].setPos(x+dx*offset, y + dy*offset)

            print('Added card ', card)


    def dealHands(self):

        hands = [self.p1_hand, self.p2_hand]

        for player in range(1, 3):

            dx = self.defHandSpacing
            dy = 0

            x, y, ang = self.playersHandsPos[player-1]

            for offset in range(8):

                card = hands[player-1][offset]

                faceDown = False

                if (player == 2):
                    faceDown = True

                card_graphics = self.addCard(card, player, faceDown)
                self.getCardsList()[0].setPos(x+dx*offset, y + dy*offset)

                if (player == 1):
                    self.p1_hand_graphics.append(card_graphics)

        print('p1 hand graphics: ', self.p1_hand_graphics)


    def unrotate_card(self, card_graphics, player):
        '''Called for drawing a discarded hand.'''

        x = card_graphics.pos().x()
        y = card_graphics.pos().y()

        print('Initial x: ', x)
        print('Initial y: ', y)

        card = card_graphics.card

        faceDown = False
        ang = 0

        z = self.last_p1_card_z

        self.removeCard(card_graphics)

        new_card_graphics = self.addCard(card, player, faceDown)
        new_card_graphics.setPos(x, y)
        new_card_graphics.rotate(ang)
        new_card_graphics.setZValue(z)

        return new_card_graphics


    def rotate_card(self, card_graphics, player):
        '''Called for discarding a card in the hand.'''

        x = card_graphics.pos().x()
        y = card_graphics.pos().y()

        print('Initial x: ', x)
        print('Initial y: ', y)

        card = card_graphics.card

        faceDown = False
        ang = 90

        suit = int(card / 13)    
        n_discarded = len(self.all_discarded[suit])

        z = n_discarded + 1

        self.removeCard(card_graphics)

        new_card_graphics = self.addCard(card, player, faceDown)
        new_card_graphics.setPos(x, y)
        new_card_graphics.rotate(ang)
        new_card_graphics.setZValue(z)

        return new_card_graphics


    def flip_card(self, card_graphics, player, old_z=None):

        x = card_graphics.pos().x()
        y = card_graphics.pos().y()

        card = card_graphics.card
        old_z = card_graphics.zValue()

        faceDown = False
        ang = 0

        if (not old_z):
            old_z = card_graphics.zValue()

        self.removeCard(card_graphics)
        #self.scene.removeItem(card_graphics)

        new_card_graphics = self.addCard(card, player, faceDown)
        new_card_graphics.setPos(x, y)
        new_card_graphics.setZValue(old_z)
        new_card_graphics.rotate(ang)
        #self.scene.addItem(new_card_graphics)

        return new_card_graphics


    def dealDeck(self):

        player = 0
        faceDown = True
        ang = 90

        (x, y, ang) = self.deckPos

        print('deck: ', self.deck)

        for card in self.deck:

            card_graphics = self.addCard(card, player, faceDown)
            self.getCardsList()[0].setPos(x, y)
            self.getCardsList()[0].rotate(ang)



    def dealDiscards(self):

        player = 0

        for suit in range(4):

            discard_suit = self.discarded_cards[suit]

            (x, y, ang) = self.discardPos[suit]
            print('y: ', y)

            for card in discard_suit:

                self.addCard(card, player)
                self.getCardsList()[0].setPos(x, y)
                self.getCardsList()[0].rotate(ang)


    def dealPlayed(self):

        for player in range(1, 3):

            played_cards = self.all_played[player-1]

            if (player == 1):
                dy = self.boardSpacing
            else:
                dy = -1 * self.boardSpacing

            for suit in range(4):

                n_cards_laid = 0

                played_suit = played_cards[suit]

                (x, y, ang) = self.boardPos[player-1][suit]

                if (played_suit):

                    for card in played_suit:

                        card_x = x
                        card_y = y + n_cards_laid * dy

                        print('card: ', card, 'player: ', player, ', x: ', card_x, 'y: ', card_y)

                        self.addCard(card, player)
                        self.getCardsList()[0].setPos(x, y + n_cards_laid * dy)
                        self.getCardsList()[0].rotate(ang)

                        n_cards_laid += 1




    def update_scene(action, player):
        pass



def main():

    app = QApplication(sys.argv)
    form = cardTableWidget()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()
